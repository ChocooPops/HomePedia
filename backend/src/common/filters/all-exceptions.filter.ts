import { ArgumentsHost, Catch, ExceptionFilter, HttpException, HttpStatus, Logger } from '@nestjs/common';
import { Response } from 'express';
import { QueryFailedError } from 'typeorm';

/** Format d'erreur uniforme : { statusCode, error, message, ...détails }. */
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger(AllExceptionsFilter.name);

  catch(exception: unknown, host: ArgumentsHost) {
    const res = host.switchToHttp().getResponse<Response>();

    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const body = exception.getResponse();
      res.status(status).json(typeof body === 'string' ? { statusCode: status, message: body } : { statusCode: status, ...body });
      return;
    }

    if (exception instanceof QueryFailedError) {
      this.logger.error(exception.message);
      res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
        statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
        error: 'DatabaseError',
        message: 'Erreur lors de l’accès à la base de données',
      });
      return;
    }

    this.logger.error(exception instanceof Error ? exception.stack : String(exception));
    res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
      error: 'InternalError',
      message: 'Erreur interne',
    });
  }
}
